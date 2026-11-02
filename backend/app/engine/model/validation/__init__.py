"""Cross-reference validation for a shape-valid engine model.

Pydantic settles the *shape* of a model document; these rules settle whether its references hang
together. Each rule raises :class:`ModelReferenceError` with the JSON pointer of the node that
failed, so a diagnostic's ``path`` is produced where the offending keys are known rather than
recovered from the message afterwards.

Rules run in a fixed order and the first rule to find a violation ends the pass. A rule that can go
on after a violation (the detail pages and their panels) raises :class:`ModelReferenceErrors` with
every problem it found; the other rules still stop at their first.
"""

from collections.abc import Callable

from ....models.schema import EngineModel
from ..diagnostics import (
    ModelDiagnostic,
    ModelReferenceError,
    ModelReferenceErrors,
    ModelValidationError,
)
from . import (
    application_rules,
    attribute_rules,
    consumer_api_rules,
    object_type_rules,
    relation_rules,
)
from .index import ModelIndex, build_index

Rule = Callable[[EngineModel, ModelIndex], None]

RULES: tuple[Rule, ...] = (
    attribute_rules.check,
    relation_rules.check_relation_type_keys,
    object_type_rules.check,
    relation_rules.check_object_type_relations,
    relation_rules.check_parent_relations,
    application_rules.check,
    consumer_api_rules.check,
)


def validate_references(model: EngineModel) -> tuple[ModelDiagnostic, ...]:
    """Return the cross-reference violations of the first rule that finds any in ``model`` (one, or
    every problem of the detail pages), or an empty tuple."""
    try:
        index = build_index(model)
        for rule in RULES:
            rule(model, index)
    except ModelReferenceError as exc:
        return (exc.as_diagnostic(),)
    except ModelReferenceErrors as exc:
        return tuple(error.as_diagnostic() for error in exc.errors)
    return ()


def require_valid_references(model: EngineModel) -> EngineModel:
    """Return ``model`` when its references resolve, otherwise raise."""
    diagnostics = validate_references(model)
    if diagnostics:
        raise ModelValidationError(diagnostics)
    return model


__all__ = [
    "RULES",
    "ModelIndex",
    "build_index",
    "require_valid_references",
    "validate_references",
]
