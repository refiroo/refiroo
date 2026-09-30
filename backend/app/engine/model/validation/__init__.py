"""Cross-reference validation for a shape-valid engine model.

Pydantic settles the *shape* of a model document; these rules settle whether its references hang
together. Each rule raises :class:`ModelReferenceError` with the JSON pointer of the node that
failed, so a diagnostic's ``path`` is produced where the offending keys are known rather than
recovered from the message afterwards.

Rules run in a fixed order and the first violation ends the pass, matching the single-diagnostic
contract the API has always exposed for reference errors. Collecting every violation instead would
only mean dropping the ``return`` in :func:`validate_references`.
"""

from collections.abc import Callable

from ....models.schema import EngineModel
from ..diagnostics import ModelDiagnostic, ModelReferenceError, ModelValidationError
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
    """Return the first cross-reference violation in ``model``, or an empty tuple."""
    try:
        index = build_index(model)
        for rule in RULES:
            rule(model, index)
    except ModelReferenceError as exc:
        return (exc.as_diagnostic(),)
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
