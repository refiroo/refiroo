"""Diagnostic types shared by model compilation, reference validation and compatibility."""

from dataclasses import dataclass
from typing import Literal

Severity = Literal["error", "warning"]


@dataclass(frozen=True)
class ModelDiagnostic:
    severity: Severity
    code: str
    path: str
    message: str
    count: int | None = None


class ModelReferenceError(Exception):
    """A cross-reference rule violation, carrying the pointer of the node that failed.

    Rules raise this at the point of detection, where the offending keys are still in hand, so the
    JSON pointer never has to be reconstructed from the message text afterwards.
    """

    def __init__(self, code: str, path: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.path = path
        self.message = message

    def as_diagnostic(self) -> ModelDiagnostic:
        return ModelDiagnostic(
            severity="error", code=self.code, path=self.path, message=self.message
        )


class ModelValidationError(Exception):
    """Raised where an invalid model must not be constructed at all."""

    def __init__(self, diagnostics: tuple[ModelDiagnostic, ...]) -> None:
        super().__init__(
            "; ".join(item.message for item in diagnostics) or "Model validation failed"
        )
        self.diagnostics = diagnostics
