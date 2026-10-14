"""A model draft changed by operations, with its history, undo and redo (0.10 A2, ADR-041, D4, D8).

A request is applied all or none at ``expectedVersion`` and becomes one **step** of the draft's
history: one entry per operation, with its parameters, its inverse (stored when applied), the draft
version it produced and the elements it created, re-keyed and named. Undo applies a step's inverses,
last entry first, as a new step of origin ``undo`` and marks the step undone by it; redo undoes that
undo (D32). A step that a later, not undone step depends on is not undone alone (D8).
"""

import copy
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ....common.time import as_utc
from ....errors import ApiError, api_error
from ....models.database import ModelDraft, ModelDraftOperation
from ...sources import draft_profile
from ..compiler import ModelDiagnostic, compile_authored_model
from ..drafts import load_draft_for_update, update_draft
from .document import PROFILE, PROFILE_IDENTITIES, Document, Refusal
from .kinds import INTERNAL_KINDS, Applied, Context, MigrationRequired, apply_operation, element_of
from .released import base_release, impact, released_atoms

# The newer entries a VERSION_CONFLICT carries before it says there are more (API.md).
CONFLICT_ENTRIES = 100
_UNDOABLE = ("request", "patch", "redo", "proposal")


@dataclass(frozen=True)
class StepResult:
    draft: ModelDraft
    entries: list[ModelDraftOperation]
    valid: bool
    # The model's diagnostics, then the draft profile's warnings (0.10 A5).
    diagnostics: tuple[ModelDiagnostic, ...]
    # What the step applied, as the dry run after it reads them (D79).
    operations: tuple[dict[str, Any], ...] = ()


def apply_request(
    session: Session, draft_id: str, expected_version: int, operations: list[dict[str, Any]], max_items: int
) -> StepResult:
    if len(operations) > max_items:
        raise api_error(
            413,
            "OPERATION_BATCH_TOO_LARGE",
            f"A request holds at most {max_items} operations",
            {"limit": max_items, "received": len(operations)},
        )
    draft = _locked(session, draft_id, expected_version)
    for index, operation in enumerate(operations):
        if isinstance(operation, dict) and operation.get("kind") in INTERNAL_KINDS:
            raise _invalid(index, Refusal("kind", "internalKind", f"'{operation['kind']}' is written by the server"))
    applied = _apply(session, draft, operations, pointer="operations")
    return _commit_step(session, draft, expected_version, operations, applied, {"type": "request"})


# What a step's origin is made of once its operations applied: what each did, the model, the profile.
OriginOf = Callable[[list[Applied], dict[str, Any], dict[str, Any] | None], dict[str, Any]]


def apply_steps(
    session: Session,
    draft_id: str,
    expected_version: int,
    steps: list[tuple[str, list[dict[str, Any]], OriginOf]],
    max_items: int,
) -> StepResult:
    """Several steps in one request, all or none, each one step of the history with the origin
    ``origin_of`` gives it once its operations applied (0.10 A6: the proposals an inference
    applies, D89). A refusal names the step it came from in ``details.step``."""
    draft = _locked(session, draft_id, expected_version)
    entries: list[ModelDraftOperation] = []
    operations: list[dict[str, Any]] = []
    result: StepResult | None = None
    for name, step_operations, origin_of in steps:
        if len(step_operations) > max_items:
            raise api_error(
                413,
                "OPERATION_BATCH_TOO_LARGE",
                f"A step holds at most {max_items} operations",
                {"limit": max_items, "received": len(step_operations), "step": name},
            )
        try:
            applied = _apply(session, draft, step_operations, pointer="operations")
        except ApiError as error:
            if isinstance(error.details, dict):
                error.details["step"] = name
            raise
        result = _commit_step(session, draft, draft.version, step_operations, applied, origin_of(*applied))
        draft = result.draft
        entries += result.entries
        operations += step_operations
    if result is None:
        raise api_error(409, "NOTHING_TO_APPLY", "The request holds no step to apply")
    return StepResult(draft, entries, result.valid, result.diagnostics, tuple(operations))


def undo(
    session: Session, draft_id: str, expected_version: int, step: int | None, steps: list[int] | None
) -> StepResult:
    draft = _locked(session, draft_id, expected_version)
    rows = _rows(session, draft)
    by_step = _steps(rows)
    undoable = [s for s, entries in by_step.items() if _is_undoable(entries)]
    wanted = sorted(set(steps or ([step] if step is not None else undoable[-1:])))
    if not wanted:
        raise api_error(409, "NOTHING_TO_UNDO", "The draft has no step to undo")
    for value in wanted:
        if value not in undoable:
            raise api_error(409, "NOTHING_TO_UNDO", f"Step {value} cannot be undone", {"step": value})
    dependants = _dependants(by_step, set(wanted), undoable)
    if dependants:
        raise api_error(
            409,
            "OPERATION_HAS_DEPENDANTS",
            "Later steps depend on what this step created or re-keyed; undo them with it",
            {"steps": wanted, "dependants": dependants},
        )
    inverses = [row.inverse for value in reversed(wanted) for row in reversed(by_step[value])]
    applied = _apply(session, draft, inverses, pointer="steps")
    result = _commit_step(session, draft, expected_version, inverses, applied, {"type": "undo", "steps": wanted})
    new_step = result.entries[0].step if result.entries else None
    for value in wanted:
        for row in by_step[value]:
            row.undone_by_step = new_step
    session.flush()
    return result


def redo(session: Session, draft_id: str, expected_version: int) -> StepResult:
    draft = _locked(session, draft_id, expected_version)
    by_step = _steps(_rows(session, draft))
    candidate = None
    for value in sorted(by_step, reverse=True):
        entries = by_step[value]
        kind = entries[0].origin.get("type")
        if kind == "undo" and entries[0].undone_by_step is None:
            candidate = value
            break
        if kind in ("request", "patch", "proposal"):
            break
    if candidate is None:
        raise api_error(409, "NOTHING_TO_REDO", "The draft has no undone step to redo")
    inverses = [row.inverse for row in reversed(by_step[candidate])]
    applied = _apply(session, draft, inverses, pointer="steps")
    result = _commit_step(session, draft, expected_version, inverses, applied, {"type": "redo", "step": candidate})
    for row in by_step[candidate]:
        row.undone_by_step = result.entries[0].step if result.entries else None
    session.flush()
    return result


def record_patch(session: Session, draft: ModelDraft, previous: dict[str, Any]) -> None:
    """A whole-model PATCH as one ``replaceModel`` step of origin ``patch`` (ADR-041)."""
    applied = Applied(
        {"model": copy.deepcopy(draft.model_json)}, {"kind": "replaceModel", "model": previous}
    )
    _write_entries(session, draft, [{"kind": "replaceModel"}], [applied], {"type": "patch"})


def conflict(session: Session, draft: ModelDraft, expected_version: int) -> Exception:
    """``409 VERSION_CONFLICT`` with the entries applied since ``expectedVersion`` (D10)."""
    rows = list(
        session.scalars(
            select(ModelDraftOperation)
            .where(ModelDraftOperation.draft_id == draft.id, ModelDraftOperation.draft_version > expected_version)
            .order_by(ModelDraftOperation.sequence)
            .limit(CONFLICT_ENTRIES + 1)
        )
    )
    details: dict[str, Any] = {
        "expectedVersion": expected_version,
        "actualVersion": draft.version,
        "operations": [entry_response(row) for row in rows[:CONFLICT_ENTRIES]],
    }
    if len(rows) > CONFLICT_ENTRIES:
        details["more"] = True
    return api_error(409, "VERSION_CONFLICT", f"Model draft '{draft.public_id}' has changed", details)


def entry_response(row: ModelDraftOperation) -> dict[str, Any]:
    return {
        "sequence": row.sequence,
        "step": row.step,
        "kind": row.kind,
        "parameters": row.parameters,
        "inverse": row.inverse,
        "draftVersion": row.draft_version,
        "author": row.author,
        "at": as_utc(row.created_at).isoformat().replace("+00:00", "Z"),
        "undone": row.undone_by_step is not None,
        # A proposal step's snapshot is for ownership (0.10 A6, D92), not for readers.
        "origin": {k: v for k, v in (row.origin or {}).items() if k != "snapshot"},
    }


# --- internals ---


def _locked(session: Session, draft_id: str, expected_version: int) -> ModelDraft:
    draft = load_draft_for_update(session, draft_id)
    if draft.version != expected_version:
        raise conflict(session, draft, expected_version)
    return draft


def _apply(
    session: Session, draft: ModelDraft, operations: list[dict[str, Any]], pointer: str
) -> tuple[list[Applied], dict[str, Any], dict[str, Any] | None]:
    """The operations applied in order to copies of the draft's model and import profile: what
    each did, the model and the profile."""
    base = base_release(session, draft)
    released = released_atoms(base.model_json if base else None)
    document = Document(copy.deepcopy(draft.model_json))
    profile = Document(
        copy.deepcopy(draft.profile_json or {}), name=PROFILE, identities=PROFILE_IDENTITIES, log=document.log
    )
    sheets, file_name = draft_profile.sheets(session, draft)
    context = Context(document, released.__contains__, profile, sheets, file_name)
    applied: list[Applied] = []
    for index, operation in enumerate(operations):
        if not isinstance(operation, dict):
            raise _invalid(index, Refusal("", "invalidValue", "An operation is an object with a kind"), pointer)
        document.log.clear()
        try:
            applied.append(apply_operation(context, operation))
        except Refusal as refusal:
            raise _invalid(index, refusal, pointer) from refusal
        except MigrationRequired as exc:
            raise api_error(
                409,
                "OPERATION_REQUIRES_MIGRATION",
                "The operation changes an element of the draft's base release; that needs a migration",
                {
                    "index": index,
                    "kind": operation.get("kind"),
                    "element": element_of(exc.element),
                    "baseReleaseId": base.public_id if base else None,
                    "impact": impact(session, exc.element),
                },
            ) from exc
    return applied, document.data, profile.data or None


def _invalid(index: int, refusal: Refusal, pointer: str = "operations") -> Exception:
    field = f"/{refusal.field}" if refusal.field else ""
    return api_error(
        422,
        "INVALID_OPERATION",
        refusal.message,
        {"index": index, "pointer": f"/{pointer}/{index}{field}", "reason": refusal.reason},
    )


def _commit_step(
    session: Session,
    draft: ModelDraft,
    expected_version: int,
    operations: list[dict[str, Any]],
    result: tuple[list[Applied], dict[str, Any], dict[str, Any] | None],
    origin: dict[str, Any],
) -> StepResult:
    applied, model, profile = result
    draft = update_draft(session, draft.public_id, expected_version, name=None, model=model, profile=profile)
    entries = _write_entries(session, draft, operations, applied, origin)
    compiled = compile_authored_model(draft.model_json)
    warnings = draft_profile.diagnostics(draft.profile_json, compiled.model if compiled.valid else None)
    return StepResult(draft, entries, compiled.valid, (*compiled.diagnostics, *warnings), tuple(operations))


def _write_entries(
    session: Session,
    draft: ModelDraft,
    operations: list[dict[str, Any]],
    applied: list[Applied],
    origin: dict[str, Any],
) -> list[ModelDraftOperation]:
    last = session.execute(
        select(func.max(ModelDraftOperation.sequence), func.max(ModelDraftOperation.step)).where(
            ModelDraftOperation.draft_id == draft.id
        )
    ).one()
    sequence, step = (last[0] or 0), (last[1] or 0) + 1
    now = datetime.now(UTC)
    rows = []
    for operation, result in zip(operations, applied, strict=True):
        sequence += 1
        row = ModelDraftOperation(
            draft_id=draft.id,
            sequence=sequence,
            step=step,
            kind=operation["kind"],
            parameters=result.parameters,
            inverse=result.inverse,
            draft_version=draft.version,
            author=None,
            origin=origin,
            effects={
                "created": sorted(result.created),
                "rekeyed": sorted(result.rekeyed),
                "named": sorted(result.named),
            },
            created_at=now,
        )
        session.add(row)
        rows.append(row)
    session.flush()
    return rows


def _rows(session: Session, draft: ModelDraft) -> list[ModelDraftOperation]:
    return list(
        session.scalars(
            select(ModelDraftOperation)
            .where(ModelDraftOperation.draft_id == draft.id)
            .order_by(ModelDraftOperation.sequence)
        )
    )


def _steps(rows: list[ModelDraftOperation]) -> dict[int, list[ModelDraftOperation]]:
    by_step: dict[int, list[ModelDraftOperation]] = {}
    for row in rows:
        by_step.setdefault(row.step, []).append(row)
    return by_step


def _is_undoable(entries: list[ModelDraftOperation]) -> bool:
    return entries[0].origin.get("type") in _UNDOABLE and all(row.undone_by_step is None for row in entries)


def _dependants(by_step: dict[int, list[ModelDraftOperation]], wanted: set[int], undoable: list[int]) -> list[int]:
    """Later steps, not undone and not among ``wanted``, naming an element a wanted step created or
    re-keyed (D8)."""
    found = []
    for later in undoable:
        if later in wanted or later < min(wanted):
            continue
        provided: set[str] = set()
        for value in wanted:
            if value < later:
                for row in by_step[value]:
                    provided |= set(row.effects.get("created", ())) | set(row.effects.get("rekeyed", ()))
        named: set[str] = set()
        for row in by_step[later]:
            named |= set(row.effects.get("named", ())) | set(row.effects.get("created", ()))
        if named & provided:
            found.append(later)
    return found
