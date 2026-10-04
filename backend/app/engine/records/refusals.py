"""How live data and a change set word the refusals the write rules share.

The rules in ``rules.py`` are one implementation for both contexts. Where the two contexts have
answered the same violation differently (another status, code or message), each context's answer is
an entry here, so the difference is stated once and settled by changing one entry (decision E-D4 in
``docs/BACKEND_BOUNDARIES_PLAN.md``). ``tests/test_rule_parity.py`` pins both columns.
"""

from collections.abc import Callable
from dataclasses import dataclass

from ...errors import ApiError, api_error


def duplicate_value(key: str, name: str, holder: str) -> ApiError:
    """A unique value another record holds: worded alike live and in a change set, the attribute's
    name for people and its key and the holder for programs (an E-D4 row settled in H4c)."""
    return api_error(
        409,
        "DUPLICATE_ATTRIBUTE_VALUE",
        f"Attribute '{name}' must be unique",
        {"attributeTypeKey": key, "conflictingObjectId": holder},
    )


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
    # Whether a write may stage a breach of a binding's ancestor scope, which validation then
    # reports and publishing refuses (a change set is a draft: decided in H4c, deviation 9).
    holds_scope_breaches: bool


LIVE = Refusals(
    unknown_object_type=lambda key: api_error(
        404, "UNKNOWN_OBJECT_TYPE", f"Object type '{key}' not found"
    ),
    unknown_application=lambda application, _type: api_error(
        404, "UNKNOWN_APPLICATION", f"Application '{application}' not found"
    ),
    type_not_in_application=lambda application, type_key: api_error(
        422,
        "INVALID_OBJECT_TYPE_FOR_APPLICATION",
        f"Object type '{type_key}' is not available in application '{application}'",
    ),
    unknown_relation_type=lambda key: api_error(
        422, "UNKNOWN_RELATION_TYPE", f"Relation type '{key}' not found"
    ),
    missing_parent=lambda object_id: api_error(
        404, "OBJECT_NOT_FOUND", f"Object '{object_id}' not found"
    ),
    immutable_relation=lambda _deleting: api_error(
        422,
        "IMMUTABLE_RELATION",
        "Engine-maintained relation cannot be created, updated or deleted directly",
    ),
    required_relation=lambda: api_error(
        422, "REQUIRED_RELATION", "A required relationship cannot be deleted independently"
    ),
    duplicate_value=duplicate_value,
    object_exists=lambda object_id: api_error(
        409, "OBJECT_ALREADY_EXISTS", f"An object with ID '{object_id}' already exists"
    ),
    holds_scope_breaches=False,
)

CHANGE_SET = Refusals(
    unknown_object_type=lambda key: api_error(
        422, "UNKNOWN_OBJECT_TYPE", f"Object type '{key}' is not in the pinned model"
    ),
    unknown_application=lambda application, type_key: api_error(
        422,
        "OBJECT_TYPE_NOT_IN_APPLICATION",
        f"Object type '{type_key}' is not enabled in application '{application}'",
    ),
    type_not_in_application=lambda application, type_key: api_error(
        422,
        "OBJECT_TYPE_NOT_IN_APPLICATION",
        f"Object type '{type_key}' is not enabled in application '{application}'",
    ),
    unknown_relation_type=lambda key: api_error(
        422, "UNKNOWN_RELATION_TYPE", f"Relation type '{key}' is not in the pinned model"
    ),
    missing_parent=lambda _object_id: api_error(
        422, "PARENT_WRONG_SCOPE", "Parent must be in the same application and workspace"
    ),
    immutable_relation=lambda deleting: api_error(
        422,
        "IMMUTABLE_RELATION",
        "Engine-maintained containment relations cannot be deleted directly"
        if deleting
        else "Engine-maintained containment relations are changed through object edits",
    ),
    required_relation=lambda: api_error(
        422, "REQUIRED_RELATION", "Required relationships cannot be deleted directly"
    ),
    duplicate_value=duplicate_value,
    object_exists=lambda object_id: api_error(
        409, "OBJECT_ALREADY_EXISTS", f"Object '{object_id}' already exists"
    ),
    holds_scope_breaches=True,
)
