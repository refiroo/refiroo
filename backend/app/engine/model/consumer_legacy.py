"""Model documents of schema 0.8 and earlier, whose ``consumerApis`` use the 0.8 shape (Base 0.9 C18).

Installed releases are immutable, so a stored 0.8 release is read as it was stored: its definitions
are the engine's internal form as written, every operation offered (today's behaviour), and its
canonical document and ``modelHash`` do not change. Writing one is refused: install, draft compile
and model validation answer :func:`legacy_consumer_apis_refusal` (C-D134).
"""

from typing import Any, Literal

from pydantic import Field

from ...models.schema import ConsumerApiDefinition, EngineModel
from .diagnostics import ModelDiagnostic

LEGACY_SCHEMA_VERSIONS = frozenset({"0.5", "0.6", "0.7", "0.8"})


class LegacyEngineModel(EngineModel):
    """A model document of schema 0.8 or earlier."""

    schemaVersion: Literal["0.5", "0.6", "0.7", "0.8"]  # type: ignore[assignment]
    consumerApis: tuple[ConsumerApiDefinition, ...] | None = Field(  # type: ignore[assignment]
        default=None, exclude_if=lambda value: value is None
    )


def is_legacy(source: Any) -> bool:
    return isinstance(source, dict) and source.get("schemaVersion") in LEGACY_SCHEMA_VERSIONS


def legacy_consumer_apis_refusal(source: Any) -> ModelDiagnostic | None:
    """The refusal of a new document of schema 0.8 or earlier that declares ``consumerApis``."""
    if not is_legacy(source) or source.get("consumerApis") is None:
        return None
    return ModelDiagnostic(
        severity="error",
        code="UNSUPPORTED_SCHEMA_VERSION",
        path="/schemaVersion",
        message=(
            f"Schema {source['schemaVersion']} can no longer declare consumerApis: write the model in"
            ' schema 0.9, whose consumer API definitions are described in CONSUMER_API "Definition shape"'
        ),
    )
